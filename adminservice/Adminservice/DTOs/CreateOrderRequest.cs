using System.ComponentModel.DataAnnotations;
using System.Text.Json;

namespace Adminservice.DTOs;

public class CreateOrderRequest
{
    [Required]
    [MaxLength(64)]
    public string CarUuid { get; set; } = string.Empty;

    [MaxLength(100)]
    public string? ClientTelegramId { get; set; }

    public long? ClientChatId { get; set; }

    [MaxLength(50)]
    public string? TgId { get; set; }

    public JsonElement? Car { get; set; }
}

