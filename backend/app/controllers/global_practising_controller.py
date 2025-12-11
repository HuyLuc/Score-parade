"""
GlobalPractisingController - Practising mode controller for Global Mode
Shows errors but does not deduct score
"""
from backend.app.controllers.global_controller import GlobalController


class GlobalPractisingController(GlobalController):
    """
    Practising mode controller
    - Shows errors for learning purposes
    - Does not deduct score
    - No stopping condition
    """
    
    def __init__(self, session_id: str, pose_service):
        """Initialize practising controller"""
        super().__init__(session_id, pose_service)
    
    # Note: _handle_error is not overridden
    # The base implementation does nothing, which is what we want for practising mode
    # Errors are still collected and can be viewed, but score is not affected
