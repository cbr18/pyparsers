using System;
using System.Collections.Generic;
using System.Net;
using System.Threading;
using System.Threading.Tasks;
using Adminservice.DTOs;
using Adminservice.Services;
using Adminservice.Services.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Adminservice.Controllers;

[ApiController]
[Route("api/admin/update")]
[Authorize]
public class UpdateController : ControllerBase
{
    private static readonly HashSet<string> AllowedSources = new(StringComparer.OrdinalIgnoreCase)
    {
        "dongchedi",
        "che168"
    };

    private readonly IDatahubUpdateService _datahubUpdateService;
    private readonly ILogger<UpdateController> _logger;

    public UpdateController(IDatahubUpdateService datahubUpdateService, ILogger<UpdateController> logger)
    {
        _datahubUpdateService = datahubUpdateService;
        _logger = logger;
    }

    [HttpPost("full")]
    public async Task<IActionResult> TriggerFullUpdate([FromBody] TriggerFullUpdateRequest request, CancellationToken cancellationToken)
    {
        if (!ModelState.IsValid)
        {
            return ValidationProblem(ModelState);
        }

        if (!TryNormalizeSource(request.Source, out var source, out var error))
        {
            return BadRequest(new { message = error });
        }

        try
        {
            var result = await _datahubUpdateService.TriggerFullUpdateAsync(source, cancellationToken);
            return Ok(new TriggerUpdateResponse
            {
                Source = source,
                UpdateType = "full",
                TaskId = result.TaskId!,
                Status = result.Status ?? "ok",
                Message = result.Message ?? "Full update started"
            });
        }
        catch (DatahubUpdateException ex)
        {
            _logger.LogError(ex, "Failed to trigger full update in DataHub. Source={Source}", source);
            return StatusCode((int)ex.StatusCode, new
            {
                message = "Failed to trigger full update",
                detail = ex.Message,
                response = ex.ResponseBody
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error while triggering full update. Source={Source}", source);
            return StatusCode((int)HttpStatusCode.InternalServerError, new
            {
                message = "Internal error while triggering full update",
                detail = ex.Message
            });
        }
    }

    [HttpPost("incremental")]
    public async Task<IActionResult> TriggerIncrementalUpdate([FromBody] TriggerIncrementalUpdateRequest request, CancellationToken cancellationToken)
    {
        if (!ModelState.IsValid)
        {
            return ValidationProblem(ModelState);
        }

        if (!TryNormalizeSource(request.Source, out var source, out var error))
        {
            return BadRequest(new { message = error });
        }

        if (request.LastN.HasValue && request.LastN <= 0)
        {
            return BadRequest(new { message = "lastN must be greater than zero when provided" });
        }

        try
        {
            var result = await _datahubUpdateService.TriggerIncrementalUpdateAsync(source, request.LastN, cancellationToken);
            return Ok(new TriggerUpdateResponse
            {
                Source = source,
                UpdateType = "incremental",
                TaskId = result.TaskId!,
                Status = result.Status ?? "ok",
                Message = result.Message ?? "Incremental update started"
            });
        }
        catch (DatahubUpdateException ex)
        {
            _logger.LogError(ex, "Failed to trigger incremental update in DataHub. Source={Source}", source);
            return StatusCode((int)ex.StatusCode, new
            {
                message = "Failed to trigger incremental update",
                detail = ex.Message,
                response = ex.ResponseBody
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error while triggering incremental update. Source={Source}", source);
            return StatusCode((int)HttpStatusCode.InternalServerError, new
            {
                message = "Internal error while triggering incremental update",
                detail = ex.Message
            });
        }
    }

    private static bool TryNormalizeSource(string? value, out string normalized, out string error)
    {
        normalized = string.Empty;
        error = string.Empty;

        if (string.IsNullOrWhiteSpace(value))
        {
            error = "Source is required";
            return false;
        }

        foreach (var allowed in AllowedSources)
        {
            if (string.Equals(value, allowed, StringComparison.OrdinalIgnoreCase))
            {
                normalized = allowed;
                return true;
            }
        }

        error = $"Unsupported source '{value}'. Allowed values: {string.Join(", ", AllowedSources)}";
        return false;
    }
}



