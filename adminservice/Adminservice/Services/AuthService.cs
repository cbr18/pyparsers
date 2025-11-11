using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Adminservice.Data;
using Adminservice.DTOs;
using Adminservice.Models;
using BCrypt.Net;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

namespace Adminservice.Services;

public interface IAuthService
{
    Task<UserDto> RegisterAsync(RegisterRequest request);
    Task<LoginResponse> LoginAsync(LoginRequest request);
}

public class AuthService : IAuthService
{
    private readonly AdminDbContext _context;
    private readonly IConfiguration _configuration;

    public AuthService(AdminDbContext context, IConfiguration configuration)
    {
        _context = context;
        _configuration = configuration;
    }

    public async Task<UserDto> RegisterAsync(RegisterRequest request)
    {
        // Проверка на существующего пользователя
        if (await _context.Users.AnyAsync(u => u.Login == request.Login))
        {
            throw new InvalidOperationException("User with this login already exists");
        }

        // Хеширование пароля
        var hashedPassword = BCrypt.Net.BCrypt.HashPassword(request.Password);

        // Создание пользователя
        var user = new User
        {
            Login = request.Login,
            HashPassword = hashedPassword,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        _context.Users.Add(user);
        await _context.SaveChangesAsync();

        return new UserDto
        {
            Id = user.Id,
            Login = user.Login,
            TgIdId = user.TgIdId,
            CreatedAt = user.CreatedAt,
            UpdatedAt = user.UpdatedAt
        };
    }

    public async Task<LoginResponse> LoginAsync(LoginRequest request)
    {
        // Поиск пользователя
        var user = await _context.Users
            .FirstOrDefaultAsync(u => u.Login == request.Login);

        if (user == null || !BCrypt.Net.BCrypt.Verify(request.Password, user.HashPassword))
        {
            throw new UnauthorizedAccessException("Invalid login or password");
        }

        // Генерация JWT токена
        var token = GenerateJwtToken(user);

        return new LoginResponse
        {
            Token = token,
            User = new UserDto
            {
                Id = user.Id,
                Login = user.Login,
                TgIdId = user.TgIdId,
                CreatedAt = user.CreatedAt,
                UpdatedAt = user.UpdatedAt
            }
        };
    }

    private string GenerateJwtToken(User user)
    {
        var jwtSettings = _configuration.GetSection("Jwt");
        var secretKey = Environment.GetEnvironmentVariable("JWT_SECRET_KEY") 
            ?? jwtSettings["SecretKey"] 
            ?? throw new InvalidOperationException("JWT secret key is not configured");

        var key = Encoding.UTF8.GetBytes(secretKey);
        var tokenDescriptor = new SecurityTokenDescriptor
        {
            Subject = new ClaimsIdentity(new[]
            {
                new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
                new Claim(ClaimTypes.Name, user.Login)
            }),
            Expires = DateTime.UtcNow.AddMinutes(int.Parse(jwtSettings["ExpiresInMinutes"] ?? "1440")),
            Issuer = jwtSettings["Issuer"] ?? "adminservice",
            Audience = jwtSettings["Audience"] ?? "adminweb",
            SigningCredentials = new SigningCredentials(
                new SymmetricSecurityKey(key),
                SecurityAlgorithms.HmacSha256Signature
            )
        };

        var tokenHandler = new JwtSecurityTokenHandler();
        var token = tokenHandler.CreateToken(tokenDescriptor);
        return tokenHandler.WriteToken(token);
    }
} 