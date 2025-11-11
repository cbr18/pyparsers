using System;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Adminservice.Data;
using Adminservice.DTOs;
using Adminservice.Models;
using System.Security.Claims;

namespace Adminservice.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class UsersController : ControllerBase
{
    private readonly AdminDbContext _context;

    public UsersController(AdminDbContext context)
    {
        _context = context;
    }


    private static UserDto ToDto(User user) => new UserDto
    {
        Id = user.Id,
        Login = user.Login,
        TgIdId = user.TgIdId,
        CreatedAt = user.CreatedAt,
        UpdatedAt = user.UpdatedAt
    };
    [HttpGet("me")]
    public async Task<ActionResult<UserDto>> GetCurrentUser()
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null || !Guid.TryParse(userIdClaim.Value, out var userId))
        {
            return Unauthorized();
        }

        var user = await _context.Users
            .Where(u => u.Id == userId)
            .Select(u => ToDto(u))
            .FirstOrDefaultAsync();

        if (user == null)
        {
            return NotFound();
        }

        return Ok(user);
    }

    [HttpGet]
    public async Task<ActionResult<List<UserDto>>> GetUsers()
    {
        var users = await _context.Users
            .OrderByDescending(u => u.CreatedAt)
            .Select(u => ToDto(u))
            .ToListAsync();

        return Ok(users);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<UserDto>> GetUser(Guid id)
    {
        var user = await _context.Users
            .Where(u => u.Id == id)
            .Select(u => ToDto(u))
            .FirstOrDefaultAsync();

        if (user == null)
        {
            return NotFound();
        }

        return Ok(user);
    }
    [HttpPost]
    public async Task<ActionResult<UserDto>> CreateUser([FromBody] CreateUserRequest request)
    {
        if (!ModelState.IsValid)
        {
            return ValidationProblem(ModelState);
        }

        if (await _context.Users.AnyAsync(u => u.Login == request.Login))
        {
            return Conflict(new { message = "User with this login already exists" });
        }

        var now = DateTime.UtcNow;
        var user = new User
        {
            Login = request.Login,
            HashPassword = BCrypt.Net.BCrypt.HashPassword(request.Password),
            TgIdId = request.TgIdId,
            CreatedAt = now,
            UpdatedAt = now
        };

        _context.Users.Add(user);
        await _context.SaveChangesAsync();

        var dto = ToDto(user);
        return CreatedAtAction(nameof(GetUser), new { id = user.Id }, dto);
    }

    [HttpPut("{id}")]
    public async Task<ActionResult<UserDto>> UpdateUser(Guid id, [FromBody] UpdateUserRequest request)
    {
        if (!ModelState.IsValid)
        {
            return ValidationProblem(ModelState);
        }

        var user = await _context.Users.FirstOrDefaultAsync(u => u.Id == id);
        if (user == null)
        {
            return NotFound();
        }

        if (!string.IsNullOrWhiteSpace(request.Login) && !string.Equals(request.Login, user.Login, StringComparison.Ordinal))
        {
            var loginExists = await _context.Users.AnyAsync(u => u.Login == request.Login && u.Id != id);
            if (loginExists)
            {
                return Conflict(new { message = "Another user with this login already exists" });
            }

            user.Login = request.Login.Trim();
        }

        if (!string.IsNullOrEmpty(request.Password))
        {
            user.HashPassword = BCrypt.Net.BCrypt.HashPassword(request.Password);
        }

        if (request.TgIdId.HasValue)
        {
            user.TgIdId = request.TgIdId;
        }
        else if (request.ClearTgId)
        {
            user.TgIdId = null;
        }

        user.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return Ok(ToDto(user));
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteUser(Guid id)
    {
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Id == id);
        if (user == null)
        {
            return NotFound();
        }

        _context.Users.Remove(user);
        await _context.SaveChangesAsync();

        return NoContent();
    }

}










