using System.Threading;
using System.Threading.Tasks;
using Adminservice.Services.Models;

namespace Adminservice.Services;

public interface IDatahubUpdateService
{
    Task<DatahubTaskResponse> TriggerFullUpdateAsync(string source, CancellationToken cancellationToken);
    Task<DatahubTaskResponse> TriggerIncrementalUpdateAsync(string source, int? lastN, CancellationToken cancellationToken);
}



