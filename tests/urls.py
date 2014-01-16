from objectset.resources import get_url_patterns
from .models import RecordSet, ProtectedRecordSet


urlpatterns = get_url_patterns(RecordSet) + \
    get_url_patterns(ProtectedRecordSet, prefix='protected')
