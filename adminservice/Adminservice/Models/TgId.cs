using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Adminservice.Models;

[Table("tg_ids")]
public class TgId : BaseRecord
{
    [Required]
    [MaxLength(50)]
    [Column("telegram_id")]
    public string TelegramId { get; set; } = string.Empty;

    [Column("chat_id")]
    public long? ChatId { get; set; }

    [Column("is_active")]
    public bool IsActive { get; set; } = true;

    public virtual ICollection<User> Users { get; set; } = new List<User>();
} 