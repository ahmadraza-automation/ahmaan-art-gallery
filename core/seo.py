import json

from django.utils.safestring import mark_safe


def schema_json(data):
	serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
	serialized = serialized.replace('&', '\\u0026').replace('<', '\\u003C').replace('>', '\\u003E')
	return mark_safe(serialized)
