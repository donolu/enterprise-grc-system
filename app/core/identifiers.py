from collections.abc import Callable
from typing import Any, cast

from django.db import IntegrityError, models, transaction


def next_prefixed_identifier(
    model: type[Any],
    field_name: str,
    prefix: str,
    *,
    width: int = 4,
) -> str:
    """Return the next identifier by incrementing the highest existing suffix."""
    lookup = {f"{field_name}__startswith": f"{prefix}-"}
    last_identifier = (
        model.objects.filter(**lookup)
        .order_by(f"-{field_name}")
        .values_list(field_name, flat=True)
        .first()
    )

    next_number = 1
    if last_identifier:
        try:
            next_number = int(str(last_identifier).rsplit("-", 1)[1]) + 1
        except (IndexError, ValueError):
            next_number = 1

    return f"{prefix}-{next_number:0{width}d}"


def save_with_generated_identifier[T](
    instance: models.Model,
    field_name: str,
    generate_identifier: Callable[[], str],
    save: Callable[[], T],
    *,
    max_attempts: int = 5,
) -> T:
    """Save an instance with retry-on-collision for generated unique identifiers."""
    should_generate = not getattr(instance, field_name)
    attempts = max_attempts if should_generate else 1
    last_error: IntegrityError | None = None

    for _ in range(attempts):
        if should_generate:
            setattr(instance, field_name, generate_identifier())
            attempted_identifier = getattr(instance, field_name)

        try:
            with transaction.atomic():
                return save()
        except IntegrityError as exc:
            if not should_generate:
                raise
            collision_lookup = {field_name: attempted_identifier}
            instance_model = cast(Any, instance.__class__)
            if not instance_model.objects.filter(**collision_lookup).exists():
                raise
            last_error = exc
            setattr(instance, field_name, "")

    if last_error is not None:
        raise last_error

    return save()
