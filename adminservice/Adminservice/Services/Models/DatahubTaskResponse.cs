using System.Text.Json.Serialization;

namespace Adminservice.Services.Models;

public record DatahubTaskResponse(
    [property: JsonPropertyName("status")] string? Status,
    [property: JsonPropertyName("message")] string? Message,
    [property: JsonPropertyName("task_id")] string? TaskId);



