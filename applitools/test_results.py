class TestResultsStatus(object):
    """
    Status values for tests results.
    """
    Passed = "Passed"
    Unresolved = "Unresolved"
    Failed = "Failed"

    @classmethod
    def get_status(cls, status):
        status_lower = status.lower()
        if status_lower == cls.Passed.lower():
            return cls.Passed
        elif status_lower == cls.Unresolved.lower():
            return cls.Unresolved
        elif status_lower == cls.Failed.lower():
            return cls.Failed
        else:
            # Unknown status
            return status


class TestResults(object):
    """
    Eyes test results.
    """
    def __init__(self, steps=0, matches=0, mismatches=0, missing=0, exact_matches=0,
                 strict_matches=0, content_matches=0, layout_matches=0, none_matches=0, status=None):
        self.steps = steps
        self.matches = matches
        self.mismatches = mismatches
        self.missing = missing
        self.exact_matches = exact_matches
        self.strict_matches = strict_matches
        self.content_matches = content_matches
        self.layout_matches = layout_matches
        self.none_matches = none_matches
        self._status = status
        self.is_new = None
        self.url = None

    @property
    def status(self):
        return TestResultsStatus.get_status(self._status)

    @status.setter
    def status(self, status_):
        self._status = status_

    @property
    def is_passed(self):
        return (self.status is not None) and self.status.lower() == TestResultsStatus.Passed.lower()

    def to_dict(self):
        return dict(steps=self.steps, matches=self.matches, mismatches=self.mismatches,
                    missing=self.missing, exact_matches=self.exact_matches,
                    strict_matches=self.strict_matches, content_matches=self.content_matches,
                    layout_matches=self.layout_matches, none_matches=self.none_matches,
                    is_new=self.is_new, url=self.url, status=self.status)

    def __str__(self):
        if self.is_new is not None:
            is_new = "New test" if self.is_new else "Existing test"
        else:
            is_new = ""
        return "%s [ steps: %d, matches: %d, mismatches: %d, missing: %d ], URL: %s" % \
               (is_new, self.steps, self.matches, self.mismatches, self.missing, self.url)