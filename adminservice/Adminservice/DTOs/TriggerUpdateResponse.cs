namespace Adminservice.DTOs;

public class TriggerUpdateResponse
{
    public string Source { get; set; } = string.Empty;
    public string UpdateType { get; set; } = string.Empty;
    public string TaskId { get; set; } = string.Empty;
    public string Status { get; set; } = "ok";
    public string Message { get; set; } = "Update triggered";
}



