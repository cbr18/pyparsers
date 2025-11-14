using System.ComponentModel.DataAnnotations;

namespace Adminservice.DTOs;

public class TriggerIncrementalUpdateRequest
{
    [Required]
    public string Source { get; set; } = string.Empty;

    public int? LastN { get; set; }
}



