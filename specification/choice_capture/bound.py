import seams as host

from vote.tests import choice_capture_seams


def seams() -> host.Seams:
    return choice_capture_seams.seams(host)
