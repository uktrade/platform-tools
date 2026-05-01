from unittest.mock import Mock

class ScheduledJob:
    def __init__(self, sfn_client):
        self.sfn_client = sfn_client
        
    def disable_schedule(name, environment):
        return "done"

def test_disable_copilot_schedule():
    pass
    mock_client = Mock()
    
    result = ScheduledJob.disable_schedule("my-job", "dev")