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

    [Column("tg_id_id")]
    public Guid? TgIdId { get; set; }

    public virtual TgId? TgId { get; set; }
}




