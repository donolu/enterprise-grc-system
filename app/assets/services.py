"""Asset-owned read services used by cross-domain workflows."""


from .models import Asset


class AssetCalendarProvider:
    """Provide asset review dates to calendar aggregation."""

    @staticmethod
    def list_events(event_factory, *, start_date=None, end_date=None, owner=None):
        queryset = (
            Asset.objects.filter(next_review_date__isnull=False)
            .exclude(lifecycle_status__in=["retired", "disposed"])
            .select_related("owner")
        )
        if start_date:
            queryset = queryset.filter(next_review_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(next_review_date__lte=end_date)
        if owner:
            queryset = queryset.filter(owner=owner)
        return [
            event_factory(
                source_type="asset_review",
                source_id=str(asset.id),
                title=f"Asset review due: {asset.name}",
                due_date=asset.next_review_date,
                owner=asset.owner,
                source_url=f"/api/assets/assets/{asset.id}/",
                status=asset.lifecycle_status,
                module="assets",
                metadata={"asset_id": asset.asset_id, "criticality": asset.criticality},
            )
            for asset in queryset
        ]
