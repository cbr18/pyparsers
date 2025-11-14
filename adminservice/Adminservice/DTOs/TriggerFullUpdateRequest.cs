using System.ComponentModel.DataAnnotations;

namespace Adminservice.DTOs;

public class TriggerFullUpdateRequest
{
    [Required]
    public string Source { get; set; } = string.Empty;
}



