using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Adminservice.Data;
using Adminservice.DTOs;
using Adminservice.Models;

namespace Adminservice.Controllers;

[ApiController]
[Route("api/[controller]")]
public class TgIdController : ControllerBase
{
    private readonly AdminDbContext _context;

    public TgIdController(AdminDbContext context)
    {
        _context = context;
    }

    [HttpGet("list")]
    [AllowAnonymous]
    public async Task<ActionResult<List<TgIdListItemDto>>> GetTgIdList()
    {
        var tgIds = await _context.TgIds
            .Where(t => t.IsActive)
            .Select(t => new TgIdListItemDto
            {
                TelegramId = t.TelegramId,
                ChatId = t.ChatId
            })
            .ToListAsync();

        return Ok(tgIds);
    }

    [HttpGet]
    [Authorize]
    public async Task<ActionResult<List<TgIdDto>>> GetAllTgIds()
    {
        var tgIds = await _context.TgIds
            .OrderByDescending(t => t.CreatedAt)
            .Select(t => new TgIdDto
            {
                Id = t.Id,
                TelegramId = t.TelegramId,
                ChatId = t.ChatId,
                IsActive = t.IsActive,
                CreatedAt = t.CreatedAt,
                UpdatedAt = t.UpdatedAt
            })
            .ToListAsync();

        return Ok(tgIds);
    }

    [HttpGet("{id}")]
    [Authorize]
    public async Task<ActionResult<TgIdDto>> GetTgId(Guid id)
    {
        var tgId = await _context.TgIds.FindAsync(id);

        if (tgId == null)
        {
            return NotFound();
        }

        return Ok(new TgIdDto
        {
            Id = tgId.Id,
            TelegramId = tgId.TelegramId,
            ChatId = tgId.ChatId,
            IsActive = tgId.IsActive,
            CreatedAt = tgId.CreatedAt,
            UpdatedAt = tgId.UpdatedAt
        });
    }

    [HttpPost]
    [Authorize]
    public async Task<ActionResult<TgIdDto>> CreateTgId([FromBody] CreateTgIdRequest request)
    {
        // Проверка на дубликат
        if (await _context.TgIds.AnyAsync(t => t.TelegramId == request.TelegramId))
        {
            return BadRequest(new { message = "Telegram ID already exists" });
        }

        if (request.ChatId.HasValue && await _context.TgIds.AnyAsync(t => t.ChatId == request.ChatId))
        {
            return BadRequest(new { message = "Chat ID already exists" });
        }

        var tgId = new TgId
        {
            TelegramId = request.TelegramId,
            ChatId = request.ChatId,
            IsActive = request.IsActive,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        _context.TgIds.Add(tgId);
        await _context.SaveChangesAsync();

        return CreatedAtAction(nameof(GetTgId), new { id = tgId.Id }, new TgIdDto
        {
            Id = tgId.Id,
            TelegramId = tgId.TelegramId,
            ChatId = tgId.ChatId,
            IsActive = tgId.IsActive,
            CreatedAt = tgId.CreatedAt,
            UpdatedAt = tgId.UpdatedAt
        });
    }

    [HttpPut("{id}")]
    [Authorize]
    public async Task<IActionResult> UpdateTgId(Guid id, [FromBody] CreateTgIdRequest request)
    {
        var tgId = await _context.TgIds.FindAsync(id);

        if (tgId == null)
        {
            return NotFound();
        }

        // Проверка на дубликат (если изменили TelegramId)
        if (tgId.TelegramId != request.TelegramId && 
            await _context.TgIds.AnyAsync(t => t.TelegramId == request.TelegramId))
        {
            return BadRequest(new { message = "Telegram ID already exists" });
        }

        if (request.ChatId.HasValue && request.ChatId != tgId.ChatId &&
            await _context.TgIds.AnyAsync(t => t.ChatId == request.ChatId))
        {
            return BadRequest(new { message = "Chat ID already exists" });
        }

        tgId.TelegramId = request.TelegramId;
        tgId.ChatId = request.ChatId;
        tgId.IsActive = request.IsActive;
        tgId.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();

        return Ok(new TgIdDto
        {
            Id = tgId.Id,
            TelegramId = tgId.TelegramId,
            ChatId = tgId.ChatId,
            IsActive = tgId.IsActive,
            CreatedAt = tgId.CreatedAt,
            UpdatedAt = tgId.UpdatedAt
        });
    }

    [HttpDelete("{id}")]
    [Authorize]
    public async Task<IActionResult> DeleteTgId(Guid id)
    {
        var tgId = await _context.TgIds.FindAsync(id);

        if (tgId == null)
        {
            return NotFound();
        }

        _context.TgIds.Remove(tgId);
        await _context.SaveChangesAsync();

        return NoContent();
    }
} 