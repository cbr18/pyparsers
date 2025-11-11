namespace Adminservice.DTOs;

public class TgIdDto
{
    public Guid Id { get; set; }
    public string TelegramId { get; set; } = string.Empty;
    public long? ChatId { get; set; }
    public bool IsActive { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
} 