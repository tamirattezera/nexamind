from django.core.management.base import BaseCommand, CommandError

from apps.conversations.services.stale_recovery import (
    DEFAULT_BATCH_SIZE,
    recover_stale_turns,
)


class Command(BaseCommand):
    help = "Recover stale in-progress ChatTurns."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help="Maximum number of candidate ChatTurns to inspect (default: 100).",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if batch_size < 1:
            raise CommandError("--batch-size must be a positive integer.")

        recovered_count = recover_stale_turns(batch_size=batch_size)
        label = "ChatTurn" if recovered_count == 1 else "ChatTurns"
        self.stdout.write(f"Recovered {recovered_count} stale {label}.")
