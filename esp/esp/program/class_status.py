# Stores constant class status values for use throughout the app.

class ClassStatus():
    CANCELLED = -20
    REJECTED = -10
    # A new draft status for when the teacher is just working on the class details
    # but hasn't submitted it for approval
    DRAFT = -5
    UNREVIEWED = 0
    HIDDEN = 5
    ACCEPTED = 10
