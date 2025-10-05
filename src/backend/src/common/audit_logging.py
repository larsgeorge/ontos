# This module previously contained an @audit_action decorator that was never used.
# The decorator approach was abandoned because it cannot handle request-specific JSON detail construction.
# Routes now manually call audit_manager.log_action_background() with custom details.
#
# This file is kept for backward compatibility but may be removed in the future. 