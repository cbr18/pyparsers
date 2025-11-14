using Adminservice.Models;

namespace Adminservice.DTOs;

public class OrderDto
{
    public Guid Id { get; set; }
    public string CarUuid { get; set; } = string.Empty;
    public string? ClientTelegramId { get; set; }
    public long? ClientChatId { get; set; }
    public string? TgId { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public static OrderDto FromEntity(Order order)
    {
        return new OrderDto
        {
            Id = order.Id,
            CarUuid = order.CarUuid,
            ClientTelegramId = order.ClientTelegramId,
            ClientChatId = order.ClientChatId,
            TgId = order.TgId,
            CreatedAt = order.CreatedAt,
            UpdatedAt = order.UpdatedAt
        };
    }
}




