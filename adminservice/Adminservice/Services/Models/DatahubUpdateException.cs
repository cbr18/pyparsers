using System.Net;

namespace Adminservice.Services.Models;

public class DatahubUpdateException : Exception
{
    public HttpStatusCode StatusCode { get; }
    public string? ResponseBody { get; }

    public DatahubUpdateException(string message, HttpStatusCode statusCode, string? responseBody, Exception? innerException = null)
        : base(message, innerException)
    {
        StatusCode = statusCode;
        ResponseBody = responseBody;
    }
}



