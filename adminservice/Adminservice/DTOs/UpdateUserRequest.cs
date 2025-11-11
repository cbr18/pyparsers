using System.ComponentModel.DataAnnotations;

namespace Adminservice.DTOs;

public class UpdateUserRequest
{
    [MaxLength(100)]
    public string? Login { get; set; }

    [MinLength(6)]
    [MaxLength(200)]
    public string? Password { get; set; }

    public Guid? TgIdId { get; set; }

    public bool ClearTgId { get; set; }
}
