from esp.program.controllers.lottery import LotteryAssignmentController
prog = Program.objects.get(pk=85)
lac = LotteryAssignmentController(prog)
lac.options['check_grade'] = False
lac.options['Kp'] = 1.15
lac.options['Ki'] = 1.1

while True:
    print "Run ... ",
    lac.compute_assignments()
    s = lac.compute_stats()
    print s['overall_utility']
    if (s['overall_utility'] > 4.09):
        break
