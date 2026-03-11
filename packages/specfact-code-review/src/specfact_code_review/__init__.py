"""specfact-code-review package entrypoint."""

from specfact_code_review.review import app as review_app_module


app = review_app_module.app
export_from_bundle = review_app_module.export_from_bundle
import_to_bundle = review_app_module.import_to_bundle
sync_with_bundle = review_app_module.sync_with_bundle
validate_bundle = review_app_module.validate_bundle

__all__ = ("app", "export_from_bundle", "import_to_bundle", "sync_with_bundle", "validate_bundle")
