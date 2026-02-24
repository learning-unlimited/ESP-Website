import pytest

from esp.program.modules.handlers.schedulingcheckmodule import (
    SchedulingCheckRunner,
    RawSCFormatter,
)

class DummyProgram:
    def getTimeSlots(self):
        return []

    def hasModule(self, name):
        return False


def test_lunch_blocks_setup_empty():
    program = DummyProgram()
    runner = SchedulingCheckRunner(program, formatter=RawSCFormatter())

    runner.lunch_blocks = []

    result = runner.lunch_blocks_setup()

    assert result == []


def test_lunch_blocks_setup_with_blocks():
    program = DummyProgram()
    runner = SchedulingCheckRunner(program, formatter=RawSCFormatter())

    runner.lunch_blocks = [["Block A", "Block B"]]

    result = runner.lunch_blocks_setup()

    assert result == ["Block A", "Block B"]