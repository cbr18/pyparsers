using System.ComponentModel.DataAnnotations;

namespace Adminservice.DTOs;

public class CreateTgIdRequest
{
    [Required]
    [MaxLength(50)]
    public string TelegramId { get; set; } = string.Empty;

    public long? ChatId { get; set; }

    public bool IsActive { get; set; } = true;
} 