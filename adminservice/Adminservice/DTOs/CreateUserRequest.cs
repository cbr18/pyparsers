using System.ComponentModel.DataAnnotations;

namespace Adminservice.DTOs;

public class CreateUserRequest
{
    [Required]
    [MaxLength(100)]
    public string Login { get; set; } = string.Empty;

    [Required]
    [MinLength(6)]
    [MaxLength(200)]
    public string Password { get; set; } = string.Empty;

    public Guid? TgIdId { get; set; }
}
