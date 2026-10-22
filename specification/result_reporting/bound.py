from adapters import build
from seams import Seams


def seams() -> Seams:
    votes, options, view_result, unavailable = build()

    def reset() -> None:
        votes.reset()
        options.reset()

    return Seams(
        reset=reset,
        vote_store=votes,
        option_store=options,
        view_result=view_result,
        unavailable=unavailable,
    )
