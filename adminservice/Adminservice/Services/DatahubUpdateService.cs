using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Adminservice.Services.Models;

namespace Adminservice.Services;

public class DatahubUpdateService : IDatahubUpdateService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<DatahubUpdateService> _logger;
    private readonly JsonSerializerOptions _serializerOptions = new(JsonSerializerDefaults.Web);

    public DatahubUpdateService(HttpClient httpClient, ILogger<DatahubUpdateService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<DatahubTaskResponse> TriggerFullUpdateAsync(string source, CancellationToken cancellationToken)
    {
        var response = await _httpClient.GetAsync($"/update/{source}/full", cancellationToken);
        return await HandleResponseAsync(response, "full", source, cancellationToken);
    }

    public async Task<DatahubTaskResponse> TriggerIncrementalUpdateAsync(string source, int? lastN, CancellationToken cancellationToken)
    {
        var payload = new { last_n = lastN };
        var response = await _httpClient.PostAsJsonAsync($"/update/{source}", payload, _serializerOptions, cancellationToken);
        return await HandleResponseAsync(response, "incremental", source, cancellationToken);
    }

    private async Task<DatahubTaskResponse> HandleResponseAsync(HttpResponseMessage response, string updateType, string source, CancellationToken cancellationToken)
    {
        var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            _logger.LogWarning("DataHub update request failed. Source={Source}, Type={Type}, StatusCode={StatusCode}, Body={Body}",
                source, updateType, (int)response.StatusCode, responseBody);
            throw new DatahubUpdateException($"DataHub responded with HTTP {(int)response.StatusCode}",
                response.StatusCode, responseBody);
        }

        try
        {
            var parsed = JsonSerializer.Deserialize<DatahubTaskResponse>(responseBody, _serializerOptions);
            if (parsed is null || string.IsNullOrWhiteSpace(parsed.TaskId))
            {
                throw new DatahubUpdateException("DataHub response is missing task identifier", response.StatusCode, responseBody);
            }

            return parsed with
            {
                Status = string.IsNullOrWhiteSpace(parsed.Status) ? "ok" : parsed.Status,
                Message = string.IsNullOrWhiteSpace(parsed.Message) ? "Task created successfully" : parsed.Message
            };
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex, "Failed to parse DataHub response. Source={Source}, Type={Type}, Body={Body}", source, updateType, responseBody);
            throw new DatahubUpdateException("Failed to parse DataHub response", response.StatusCode, responseBody, ex);
        }
    }
}

