using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Adminservice.Data;
using Adminservice.DTOs;
using Adminservice.Models;

namespace Adminservice.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class OrdersController : ControllerBase
{
    private readonly AdminDbContext _context;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IConfiguration _configuration;
    private readonly ILogger<OrdersController> _logger;

    public OrdersController(
        AdminDbContext context,
        IHttpClientFactory httpClientFactory,
        IConfiguration configuration,
        ILogger<OrdersController> logger)
    {
        _context = context;
        _httpClientFactory = httpClientFactory;
        _configuration = configuration;
        _logger = logger;
    }

    [HttpGet]
    public async Task<ActionResult<PagedResult<OrderDto>>> GetOrders(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20)
    {
        const int maxPageSize = 100;
        page = Math.Max(1, page);
        pageSize = Math.Clamp(pageSize, 1, maxPageSize);

        var query = _context.Orders
            .AsNoTracking()
            .OrderByDescending(o => o.CreatedAt);

        var totalCount = await query.CountAsync();
        var totalPages = totalCount == 0
            ? 0
            : (int)Math.Ceiling(totalCount / (double)pageSize);

        if (totalCount == 0)
        {
            page = 1;
        }
        else if (page > totalPages)
        {
            page = totalPages;
        }

        var skip = (page - 1) * pageSize;

        var orders = await query
            .Skip(skip)
            .Take(pageSize)
            .ToListAsync();

        var items = orders
            .Select(OrderDto.FromEntity)
            .ToList();

        var result = new PagedResult<OrderDto>(items, page, pageSize, totalCount);
        return Ok(result);
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<OrderDto>> GetOrder(Guid id)
    {
        var order = await _context.Orders
            .AsNoTracking()
            .FirstOrDefaultAsync(o => o.Id == id);

        if (order == null)
        {
            return NotFound();
        }

        return Ok(OrderDto.FromEntity(order));
    }

    [HttpPost]
    [AllowAnonymous]
    public async Task<ActionResult<OrderDto>> CreateOrder([FromBody] CreateOrderRequest request)
    {
        var order = new Order
        {
            CarUuid = request.CarUuid,
            ClientTelegramId = request.ClientTelegramId,
            ClientChatId = request.ClientChatId,
            TgId = string.IsNullOrWhiteSpace(request.TgId) ? request.ClientTelegramId : request.TgId,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        _context.Orders.Add(order);
        await _context.SaveChangesAsync();

        var carPayload = BuildCarPayload(request, order);
        var userLabel = !string.IsNullOrWhiteSpace(order.TgId)
            ? order.TgId!
            : (string.IsNullOrWhiteSpace(request.ClientTelegramId)
                ? "Не указан"
                : request.ClientTelegramId);

        await NotifyAdminBotAsync(order, carPayload, userLabel);
        await NotifyTelegramBotUserAsync(order, carPayload, request.ClientChatId);

        return CreatedAtAction(nameof(GetOrder), new { id = order.Id }, OrderDto.FromEntity(order));
    }

    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> DeleteOrder(Guid id)
    {
        var order = await _context.Orders.FindAsync(id);
        if (order == null)
        {
            return NotFound();
        }

        _context.Orders.Remove(order);
        await _context.SaveChangesAsync();

        return NoContent();
    }

    private Dictionary<string, object?> BuildCarPayload(CreateOrderRequest request, Order order)
    {
        Dictionary<string, object?> carPayload;

        if (request.Car.HasValue &&
            request.Car.Value.ValueKind != JsonValueKind.Null &&
            request.Car.Value.ValueKind != JsonValueKind.Undefined)
        {
            carPayload = JsonSerializer.Deserialize<Dictionary<string, object?>>(request.Car.Value.GetRawText())
                         ?? new Dictionary<string, object?>();
        }
        else
        {
            carPayload = new Dictionary<string, object?>();
        }

        if (!carPayload.TryGetValue("uuid", out var uuidValue) || IsNullOrEmpty(uuidValue))
        {
            carPayload["uuid"] = order.CarUuid;
        }

        return carPayload;
    }

    private async Task NotifyAdminBotAsync(Order order, Dictionary<string, object?> carPayload, string userLabel)
    {
        try
        {
            var baseUrl = _configuration["AdminBot:BaseUrl"]
                          ?? Environment.GetEnvironmentVariable("ADMIN_BOT_INTERNAL_URL")
                          ?? "http://adminbot:8000";

            var targetUrl = $"{baseUrl.TrimEnd('/')}/lead";
            var client = _httpClientFactory.CreateClient();
            client.Timeout = TimeSpan.FromSeconds(10);

            var response = await client.PostAsJsonAsync(targetUrl, new
            {
                car = carPayload,
                user = userLabel
            });

            if (!response.IsSuccessStatusCode)
            {
                var body = await response.Content.ReadAsStringAsync();
                _logger.LogWarning("Failed to notify admin bot about order {OrderId}. Status: {Status}. Body: {Body}",
                    order.Id, (int)response.StatusCode, body);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error notifying admin bot about new order {OrderId}", order.Id);
        }
    }

    private async Task NotifyTelegramBotUserAsync(Order order, Dictionary<string, object?> carPayload, long? clientChatId)
    {
        if (!clientChatId.HasValue)
        {
            _logger.LogDebug("Skipping user notification for order {OrderId}: chat id is missing", order.Id);
            return;
        }

        try
        {
            var baseUrl = _configuration["TelegramBot:BaseUrl"]
                          ?? Environment.GetEnvironmentVariable("TELEGRAM_BOT_INTERNAL_URL")
                          ?? "http://telegrambot:3001";

            var targetUrl = $"{baseUrl.TrimEnd('/')}/notify-user";
            var client = _httpClientFactory.CreateClient();
            client.Timeout = TimeSpan.FromSeconds(10);

            var message = BuildUserConfirmationMessage(carPayload);
            var imageUrl = TryGetString(carPayload, "image");

            var response = await client.PostAsJsonAsync(targetUrl, new
            {
                chatId = clientChatId.Value,
                message,
                imageUrl
            });

            if (!response.IsSuccessStatusCode)
            {
                var body = await response.Content.ReadAsStringAsync();
                _logger.LogWarning("Failed to notify telegram bot user about order {OrderId}. Status: {Status}. Body: {Body}",
                    order.Id, (int)response.StatusCode, body);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error notifying telegram bot user about new order {OrderId}", order.Id);
        }
    }

    private static string BuildUserConfirmationMessage(Dictionary<string, object?> carPayload)
    {
        var title = TryGetString(carPayload, "title")
                    ?? TryGetString(carPayload, "car_name")
                    ?? TryGetString(carPayload, "car_model")
                    ?? "Без названия";

        var brand = TryGetString(carPayload, "brand_name")
                    ?? TryGetString(carPayload, "brand");

        var model = TryGetString(carPayload, "car_name")
                    ?? TryGetString(carPayload, "model");

        var price = TryGetString(carPayload, "price");
        var city = TryGetString(carPayload, "city");

        var lines = new List<string>
        {
            $"✅ Заявка по машине «{title}» успешно отправлена."
        };

        if (!string.IsNullOrWhiteSpace(brand) || !string.IsNullOrWhiteSpace(model))
        {
            lines.Add("");
            if (!string.IsNullOrWhiteSpace(brand))
            {
                lines.Add($"Марка: {brand}");
            }

            if (!string.IsNullOrWhiteSpace(model))
            {
                lines.Add($"Модель: {model}");
            }
        }

        if (!string.IsNullOrWhiteSpace(price))
        {
            lines.Add($"Цена: {price}");
        }

        if (!string.IsNullOrWhiteSpace(city))
        {
            lines.Add($"Город: {city}");
        }

        lines.Add("");
        lines.Add("Мы свяжемся с вами в ближайшее время.");

        return string.Join('\n', lines);
    }

    private static string? TryGetString(Dictionary<string, object?> source, string key)
    {
        if (!source.TryGetValue(key, out var value) || value is null)
        {
            return null;
        }

        return value switch
        {
            string s => string.IsNullOrWhiteSpace(s) ? null : s,
            JsonElement jsonElement => jsonElement.ValueKind switch
            {
                JsonValueKind.Null or JsonValueKind.Undefined => null,
                JsonValueKind.String => jsonElement.GetString(),
                JsonValueKind.Number => jsonElement.ToString(),
                JsonValueKind.True or JsonValueKind.False => jsonElement.GetBoolean().ToString(),
                _ => jsonElement.ToString()
            },
            _ => value.ToString()
        };
    }

    private static bool IsNullOrEmpty(object? value)
    {
        if (value is null)
        {
            return true;
        }

        if (value is string s)
        {
            return string.IsNullOrWhiteSpace(s);
        }

        if (value is JsonElement jsonElement)
        {
            return jsonElement.ValueKind switch
            {
                JsonValueKind.Null or JsonValueKind.Undefined => true,
                JsonValueKind.String => string.IsNullOrWhiteSpace(jsonElement.GetString()),
                _ => false
            };
        }

        return false;
    }
}

