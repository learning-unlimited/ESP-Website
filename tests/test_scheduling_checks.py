import pytest

from esp.program.modules.handlers.schedulingcheckmodule import (
    SchedulingCheckRunner,
    RawSCFormatter,
)

class DummyProgram:
    """Minimal stub program object for testing."""
    def getTimeSlots(self):
        return []

    def hasModule(self, name):
        return False


def test_lunch_blocks_setup_empty():
    """Should return empty list when no lunch blocks exist."""
    program = DummyProgram()
    runner = SchedulingCheckRunner(program, formatter=RawSCFormatter())

    runner.lunch_blocks = []  # simulate no lunch blocks

    result = runner.lunch_blocks_setup()

    assert result == []