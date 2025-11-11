using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Adminservice.Models;

[Table("users")]
public class User : BaseRecord
{
    [Required]
    [MaxLength(100)]
    [Column("login")]
    public string Login { get; set; } = string.Empty;

    [Required]
    [MaxLength(255)]
    [Column("hash_password")]
    public string HashPassword { get; set; } = string.Empty;

    [Column("tg_id_id")]
    public Guid? TgIdId { get; set; }

    [ForeignKey("TgIdId")]
    public virtual TgId? TgId { get; set; }
} 