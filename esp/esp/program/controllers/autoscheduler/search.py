"""
A class for using depth-limited DFS to try to find improvements to a schedule.
"""


class SearchOptimizer:
    def __init__(self, manipulator):
        self.manipulator = manipulator

    def optimize_section(self, section, depth):
        """Tries to schedule (if it is not scheduled) or move (if it is already
        scheduled) the specified section by moving or unscheduling other
        sections, searching up to the specified depth."""
        pass
