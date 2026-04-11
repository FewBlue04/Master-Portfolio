"""Fast simulation preset for quick local checks."""

from simulate import print_summary, run_trials


def main():
    for num_bots in [1, 2, 3]:
        _, summary = run_trials(
            num_bots=num_bots,
            trials=20,
            max_turns=300,
            stall_limit=30,
            seed=42,
            debug=False,
        )
        print_summary(summary, num_bots)
        print("---")


if __name__ == "__main__":
    main()
