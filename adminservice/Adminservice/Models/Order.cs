using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Adminservice.Models;

[Table("orders")]
public class Order : BaseRecord
{
    [Required]
    [Column("car_uuid")]
    [MaxLength(64)]
    public string CarUuid { get; set; } = string.Empty;

    [Column("client_telegram_id")]
    [MaxLength(100)]
    public string? ClientTelegramId { get; set; }

    [Column("client_chat_id")]
    public long? ClientChatId { get; set; }

    [Column("tg_id")]
    [MaxLength(50)]
    public string? TgId { get; set; }
}




