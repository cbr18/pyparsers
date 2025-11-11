using Adminservice.Models;

namespace Adminservice.DTOs;

public class OrderDto
{
    public Guid Id { get; set; }
    public string CarUuid { get; set; } = string.Empty;
    public string? ClientTelegramId { get; set; }
    public Guid? TgIdId { get; set; }
    public string? LinkedTelegramId { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public static OrderDto FromEntity(Order order)
    {
        return new OrderDto
        {
            Id = order.Id,
            CarUuid = order.CarUuid,
            ClientTelegramId = order.ClientTelegramId,
            TgIdId = order.TgIdId,
            LinkedTelegramId = order.TgId?.TelegramId,
            CreatedAt = order.CreatedAt,
            UpdatedAt = order.UpdatedAt
        };
    }
}




