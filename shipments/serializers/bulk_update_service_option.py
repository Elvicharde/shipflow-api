from rest_framework import serializers

class BulkUpdateServiceAndOptionSerializer(serializers.Serializer):
    upload_session_id = serializers.CharField(required=True)
    shipments = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
