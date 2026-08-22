from __future__ import absolute_import
import json
import logging
import random
import tempfile

from django.conf import settings
from django.utils import timezone

from esp.program.models import StudentRegistration, LotteryInputSnapshot, LotteryRun
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.controllers.lottery import ilp as ilp_lottery
from esp.program.controllers.lottery.base import BaseLotteryAssignmentController, LotteryException
from esp.program.controllers.lottery.ilp import ILPLotteryAssignmentController
from esp.program.controllers.lottery.legacy import LegacyLotteryAssignmentController
from esp.program.controllers.lottery.refresh import (
    TERMINAL_STATUSES, refresh_run_from_service, resolve_solver_client, resolve_solver_client_by_name,
)
from esp.program.controllers.lottery.remote import RemoteSolverError
from esp.tagdict.models import Tag
from esp.utils.web import render_to_response
from esp.utils.decorators import json_response

logger = logging.getLogger(__name__)

class LotteryFrontendModule(ProgramModuleObj):
    doc = """Run the class lottery and assign students to classes."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Lottery Frontend",
            "link_title": "Run the Lottery Assignment Thing",
            "module_type": "manage",
            "seq": 10,
            "choosable": 0,
            }

    def _ilp_preflight_issues(self, prog):
        """Data-driven conditions that will make every ILP submission fail
        with a LotteryException, regardless of what the admin fills into the
        form -- checked upfront (cheap, no controller/DB-heavy initialize()
        needed) so the config form can be replaced with a clear list of
        blockers instead of a cryptic error after the fact. Keep in sync with
        the actual rejections in ILPLotteryAssignmentController.__init__.
        """

        issues = []

        has_grade_range_exception_regs = StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=prog, relationship__name='GradeRangeException'
        ).exists()
        if prog.useGradeRangeExceptions() or has_grade_range_exception_regs:
            issues.append(
                'This program has grade range exceptions enabled and/or GradeRangeException '
                'registrations, which are not supported by the ILP lottery algorithm.'
            )

        return issues

    def _ilp_size_cap_warnings(self, prog):
        """Program-size-cap conditions ILPLotteryAssignmentController
        silently ignores rather than rejecting (see its __init__)."""

        warnings = []

        if Tag.getProgramTag("program_size_by_grade", prog):
            warnings.append(
                'This program has the program_size_by_grade Tag set. The ILP lottery (like the '
                'legacy algorithm) does not support it and will run with no program-size cap at all.'
            )
        elif prog.program_size_max:
            warnings.append(
                'This program has a program size cap (program_size_max=%d). The ILP lottery '
                'algorithm does not enforce it and will run with no program-size cap.' % prog.program_size_max
            )

        return warnings

    @main_call
    @needs_admin
    def lottery(self, request, tl, one, two, module, extra, prog):
        #   Check that the lottery module is included
        students = self.program.students()
        if 'lotteried_students' not in students and 'twophase_star_students' not in students:
            return render_to_response(self.baseDir() + 'not_configured.html', request, {'program': prog})

        solvers = getattr(settings, 'LOTTERY_SOLVERS', {})
        ilp_available = ilp_lottery.gp is not None and bool(solvers)
        if ilp_available:
            ilp_unavailable_reason = None
        else:
            ilp_unavailable_reason = (
                'gurobipy is not installed on this server.' if ilp_lottery.gp is None
                else 'No solver services are configured (settings.LOTTERY_SOLVERS is empty).'
            )

        # Shared by both algorithms -- both call BaseLotteryAssignmentController.initialize(),
        # which will unconditionally raise a LotteryException on the first
        # problem it hits if any exist. Surface all of them up front instead.
        lottery_preflight_issues = BaseLotteryAssignmentController.find_preflight_issues(prog)

        ilp_preflight_issues = (self._ilp_preflight_issues(prog) if ilp_available else []) + lottery_preflight_issues
        ilp_size_cap_warnings = self._ilp_size_cap_warnings(prog) if ilp_available else []

        #   Render control page with lottery options
        options = [
            {'key': k, 'default': v[0], 'help': v[1], 'is_bool': isinstance(v[0], bool)}
            for k, v in LegacyLotteryAssignmentController.default_options.items()
            if v[1] is not False
        ]

        real_priority_limit = self.program.priorityLimit()
        effective_priority_limit = (
            real_priority_limit + 1 if self.program.useGradeRangeExceptions() else real_priority_limit
        )
        # Matches ILPLotteryAssignmentController's own only-known default
        # (rank_weights=[5, 2, 1], only used when effective_priority_limit == 3).
        default_rank_weights = [5, 2, 1] if effective_priority_limit == 3 else None
        rank_weight_options = [
            {'level': i, 'default': default_rank_weights[i - 1] if default_rank_weights else ''}
            for i in range(1, effective_priority_limit + 1)
        ]

        context = {
            'options': options,
            'rank_weight_options': rank_weight_options,
            'has_old_schedules': StudentRegistration.objects.filter(section__parent_class__parent_program=self.program, relationship__name='Enrolled').count() > 0,
            'ilp_available': ilp_available,
            'ilp_unavailable_reason': ilp_unavailable_reason,
            'ilp_preflight_issues': ilp_preflight_issues,
            'ilp_size_cap_warnings': ilp_size_cap_warnings,
            'lottery_preflight_issues': lottery_preflight_issues,
            'solver_names': sorted(solvers.keys()),
        }
        return render_to_response(self.baseDir()+'lottery.html', request, context)

    def is_float(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    @aux_call
    @json_response()
    @needs_admin
    def lottery_execute(self, request, tl, one, two, module, extra, prog):
        # find what options the user wants
        options = {}

        for key in request.POST:
            if 'lottery_' in key:
                value = request.POST[key]

                if value == 'True':
                    value = True
                elif value == 'False':
                    value = False
                elif value == 'None':
                    value = None
                elif self.is_float(value):
                    value = float(value)

                options[key.split('_', 1)[1]] = value

        try:
            lotteryObj = LegacyLotteryAssignmentController(prog, **options)
            lotteryObj.compute_assignments(True)
        except LotteryException as e:
            logging.exception(e)
            return {'response': [{'error_msg': str(e)}]}

        stats = lotteryObj.compute_stats()
        display_stats = lotteryObj.extract_stats(stats)
        display_charts = lotteryObj.extract_chart_stats(stats)
        lottery_data = lotteryObj.export_assignments()
        return {'response': [{'stats': display_stats, 'charts': display_charts, 'lottery_data': lottery_data}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_save(self, request, tl, one, two, module, extra, prog):
        if 'lottery_data' not in request.POST:
            return {'response': [{'success': 'no', 'error': 'missing lottery_data POST field'}]};

        lotteryObj = LegacyLotteryAssignmentController(prog)
        lotteryObj.import_assignments(request.POST['lottery_data'])
        lotteryObj.save_assignments()
        return {'response': [{'success': 'yes'}]};

    # ------------------------------------------------------------------
    # ILP lottery: async, backed by LotteryRun rows and a remote solver
    # service. See esp.program.controllers.lottery.refresh for the
    # guarded-refresh mechanics shared with the cron poller.
    # ------------------------------------------------------------------

    def _get_run_or_none(self, request, prog):
        run_id = request.POST.get('run_id')
        if not run_id:
            return None
        try:
            return LotteryRun.objects.get(id=run_id, program=prog)
        except (LotteryRun.DoesNotExist, ValueError):
            return None

    def _serialize_run(self, run):
        return {
            'id': run.id,
            'label': run.label,
            'solver_name': run.solver_name,
            'status': run.status,
            'progress': run.progress_series if isinstance(run.progress_series, list) else [],
            'error': run.error,
            'params': run.params,
            'submitted_at': run.submitted_at.isoformat() if run.submitted_at else None,
            'finished_at': run.finished_at.isoformat() if run.finished_at else None,
            'has_result': isinstance(run.enrolled_pairs, list),
            'saved_at': run.saved_at.isoformat() if run.saved_at else None,
            'archived': run.archived,
        }

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_submit(self, request, tl, one, two, module, extra, prog):
        solvers = getattr(settings, 'LOTTERY_SOLVERS', {})
        if not solvers:
            return {'response': [{'error_msg': 'No lottery solver services are configured (LOTTERY_SOLVERS is empty).'}]}

        try:
            payload = json.loads(request.POST.get('params', '{}'))
        except ValueError:
            return {'response': [{'error_msg': 'params must be valid JSON'}]}

        solver_name = payload.get('solver_name') or getattr(settings, 'LOTTERY_DEFAULT_SOLVER', None) or next(iter(solvers))
        if solver_name not in solvers:
            return {'response': [{'error_msg': 'Unknown solver %r' % solver_name}]}

        objective_params = payload.get('objective') or {}
        solve_params = dict(payload.get('solve') or {})
        # Seed is always random -- never exposed as a field, always set here.
        solve_params.setdefault('Seed', random.randint(0, 2000000000))
        label = payload.get('label') or None

        controller_kwargs = dict(objective_params)
        try:
            len_weight_preset = controller_kwargs.pop('section_len_weight_preset', 'per_section')
            if len_weight_preset == 'per_timeblock':
                controller_kwargs['section_len_to_weight'] = lambda length: length
            elif len_weight_preset != 'per_section':
                raise LotteryException('Unknown section_len_weight_preset %r' % len_weight_preset)

            raw_student_penalties = controller_kwargs.pop('empty_student_schedule_penalties', None)
            if raw_student_penalties:
                controller_kwargs['empty_student_schedule_penalties'] = {
                    int(k): v for k, v in raw_student_penalties.items()
                }

            raw_section_points = controller_kwargs.pop('empty_section_penalty_points', None)
            if raw_section_points:
                def section_penalty_points(section_id, capacity, points=raw_section_points):
                    return [(frac * capacity, penalty) for frac, penalty in points]
                controller_kwargs['empty_section_penalty_points'] = section_penalty_points

            controller = ILPLotteryAssignmentController(prog, **controller_kwargs)
            controller.build_model()
        except (LotteryException, ValueError, TypeError, AttributeError) as e:
            logger.exception(e)
            return {'response': [{'error_msg': str(e)}]}

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = "%s/model.mps.gz" % tmp_dir
            controller.model.write(tmp_path)
            with open(tmp_path, "rb") as f:
                model_bytes = f.read()
        controller.model.dispose()

        input_hash = controller.input_hash()
        snapshot, _ = LotteryInputSnapshot.objects.get_or_create(
            input_hash=input_hash,
            defaults={'program': prog, 'data': controller.encode_snapshot_blob()},
        )

        try:
            client = resolve_solver_client_by_name(solver_name, solvers)
            submit_result = client.submit(model_bytes, solve_params)
        except LotteryException as e:
            return {'response': [{'error_msg': 'Could not submit to solver service: %s' % e}]}

        run = LotteryRun.objects.create(
            program=prog,
            snapshot=snapshot,
            solver_name=solver_name,
            solver_job_id=submit_result['job_id'],
            status=submit_result.get('status', 'queued'),
            params={'objective': objective_params, 'solve': solve_params},
            label=label,
            submitted_by=request.user,
        )

        return {'response': [{'run': self._serialize_run(run)}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_status(self, request, tl, one, two, module, extra, prog):
        runs = LotteryRun.objects.filter(program=prog, archived=False).order_by('-id')
        result = []
        for run in runs:
            run = refresh_run_from_service(run)
            result.append(self._serialize_run(run))
        return {'response': [{'runs': result}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_stop(self, request, tl, one, two, module, extra, prog):
        run = self._get_run_or_none(request, prog)
        if run is None:
            return {'response': [{'error_msg': 'run not found'}]}
        if run.status in TERMINAL_STATUSES:
            return {'response': [{'run': self._serialize_run(run)}]}
        try:
            client = resolve_solver_client(run)
            client.stop(run.solver_job_id)
        except (RemoteSolverError, LotteryException) as e:
            return {'response': [{'error_msg': str(e)}]}
        return {'response': [{'run': self._serialize_run(run)}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_relabel(self, request, tl, one, two, module, extra, prog):
        run = self._get_run_or_none(request, prog)
        if run is None:
            return {'response': [{'error_msg': 'run not found'}]}
        run.label = request.POST.get('label') or None
        run.save(update_fields=['label'])
        return {'response': [{'run': self._serialize_run(run)}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_save(self, request, tl, one, two, module, extra, prog):
        run = self._get_run_or_none(request, prog)
        if run is None:
            return {'response': [{'error_msg': 'run not found'}]}
        if not isinstance(run.enrolled_pairs, list):
            return {'response': [{'error_msg': 'This run has no result to save yet.'}]}

        snapshot_data = BaseLotteryAssignmentController.decode_snapshot_blob(bytes(run.snapshot.data))
        BaseLotteryAssignmentController.save_from_pairs(
            prog, run.enrolled_pairs, lotteried_student_ids=snapshot_data['students'], try_mailman=True,
        )
        run.saved_at = timezone.now()
        run.saved_by = request.user
        run.save(update_fields=['saved_at', 'saved_by'])
        return {'response': [{'run': self._serialize_run(run)}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_archive(self, request, tl, one, two, module, extra, prog):
        run = self._get_run_or_none(request, prog)
        if run is None:
            return {'response': [{'error_msg': 'run not found'}]}
        run.archived = True
        run.save(update_fields=['archived'])
        return {'response': [{'success': 'yes'}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_archived_status(self, request, tl, one, two, module, extra, prog):
        runs = LotteryRun.objects.filter(program=prog, archived=True).order_by('-id')
        result = [self._serialize_run(run) for run in runs]
        return {'response': [{'runs': result}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_unarchive(self, request, tl, one, two, module, extra, prog):
        run = self._get_run_or_none(request, prog)
        if run is None:
            return {'response': [{'error_msg': 'run not found'}]}
        run.archived = False
        run.save(update_fields=['archived'])
        return {'response': [{'success': 'yes'}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_ilp_stats(self, request, tl, one, two, module, extra, prog):
        run = self._get_run_or_none(request, prog)
        if run is None:
            return {'response': [{'error_msg': 'run not found'}]}
        if not isinstance(run.enrolled_pairs, list):
            return {'response': [{'error_msg': 'This run has no result yet.'}]}

        snapshot_data = BaseLotteryAssignmentController.decode_snapshot_blob(bytes(run.snapshot.data))
        controller = BaseLotteryAssignmentController.from_snapshot(prog, snapshot_data, run.enrolled_pairs)
        stats = controller.compute_stats(display=False)
        display_stats = controller.extract_stats(stats)
        display_charts = controller.extract_chart_stats(stats)
        return {'response': [{'stats': display_stats, 'charts': display_charts}]}

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
