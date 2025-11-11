using System.Net.Http;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Adminservice.Controllers;

[ApiController]
[Route("api/integrations/adminbot")]
[Authorize]
public class AdminBotController : ControllerBase
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IConfiguration _configuration;
    private readonly ILogger<AdminBotController> _logger;

    public AdminBotController(
        IHttpClientFactory httpClientFactory,
        IConfiguration configuration,
        ILogger<AdminBotController> logger)
    {
        _httpClientFactory = httpClientFactory;
        _configuration = configuration;
        _logger = logger;
    }

    [HttpPost("apply-tgids")]
    public async Task<IActionResult> ApplyTelegramIdsAsync()
    {
        var baseUrl = _configuration["AdminBot:BaseUrl"]
                      ?? Environment.GetEnvironmentVariable("ADMIN_BOT_INTERNAL_URL")
                      ?? "http://adminbot:8000";

        var targetUrl = $"{baseUrl.TrimEnd('/')}/sync/telegram-ids";

        try
        {
            var client = _httpClientFactory.CreateClient();
            client.Timeout = TimeSpan.FromSeconds(15);

            using var request = new HttpRequestMessage(HttpMethod.Post, targetUrl);
            var response = await client.SendAsync(request);
            var body = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning(
                    "AdminBot sync failed with status {StatusCode}: {Body}",
                    (int)response.StatusCode,
                    body);

                return StatusCode((int)response.StatusCode, new
                {
                    message = "Failed to sync Telegram IDs in admin bot",
                    detail = body
                });
            }

            return Content(body, "application/json");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error while syncing Telegram IDs with admin bot");
            return StatusCode(500, new
            {
                message = "Internal error while syncing Telegram IDs with admin bot",
                detail = ex.Message
            });
        }
    }
}

