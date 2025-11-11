using System.Text;
using System.Linq;
using System.Data;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using Adminservice.Data;
using Adminservice.Services;
using Adminservice.Models;

var builder = WebApplication.CreateBuilder(args);

// Database
var dbHost = Environment.GetEnvironmentVariable("ADMIN_POSTGRES_HOST") ?? "admin-postgres";
var dbUser = Environment.GetEnvironmentVariable("ADMIN_POSTGRES_USER") ?? "admin_user";
var dbPassword = Environment.GetEnvironmentVariable("ADMIN_POSTGRES_PASSWORD") ?? "admin_password";
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
if (string.IsNullOrWhiteSpace(connectionString))
{
    connectionString = $"Host={dbHost};Port=5432;Database=adminservice;Username={dbUser};Password={dbPassword}";
}

builder.Services.AddDbContext<AdminDbContext>(options =>
    options.UseNpgsql(connectionString));

// Services
builder.Services.AddScoped<IAuthService, AuthService>();
builder.Services.AddHttpClient();

// Controllers with JSON options (camelCase)
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
    });

// Swagger
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo { Title = "Admin Service API", Version = "v1" });
    
    // JWT Authentication для Swagger
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Description = "JWT Authorization header using the Bearer scheme. Enter 'Bearer' [space] and then your token",
        Name = "Authorization",
        In = ParameterLocation.Header,
        Type = SecuritySchemeType.ApiKey,
        Scheme = "Bearer"
    });

    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "Bearer"
                }
            },
            Array.Empty<string>()
        }
    });
});

// JWT Authentication
var jwtSettings = builder.Configuration.GetSection("Jwt");
var secretKey = Environment.GetEnvironmentVariable("JWT_SECRET_KEY") 
    ?? jwtSettings["SecretKey"] 
    ?? "your-secret-key-min-32-characters-long-for-hs256-algorithm";

builder.Services.AddAuthentication(options =>
{
    options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(options =>
{
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true,
        ValidateAudience = true,
        ValidateLifetime = true,
        ValidateIssuerSigningKey = true,
        ValidIssuer = jwtSettings["Issuer"] ?? "adminservice",
        ValidAudience = jwtSettings["Audience"] ?? "adminweb",
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey)),
        ClockSkew = TimeSpan.Zero
    };
});

// CORS
var corsOrigins = builder.Configuration.GetSection("Cors:AllowedOrigins").Value?.Split(',')
    ?? new[] { "http://localhost:3000", "https://car-catch.ru" };

builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.WithOrigins(corsOrigins)
              .AllowAnyMethod()
              .AllowAnyHeader()
              .AllowCredentials();
    });
});

var app = builder.Build();

// Ensure database is created and migrated
using (var scope = app.Services.CreateScope())
{
    var context = scope.ServiceProvider.GetRequiredService<AdminDbContext>();
    var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();
    
    try
    {
        // Ensure database exists and apply migrations
        if (context.Database.CanConnect())
        {
            logger.LogInformation("Database connection successful. Applying migrations...");
            context.Database.Migrate();
            logger.LogInformation("Migrations applied successfully.");
        }
        else
        {
            logger.LogInformation("Database does not exist. Creating database and applying migrations...");
            context.Database.Migrate();
            logger.LogInformation("Database created and migrations applied successfully.");
        }
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "An error occurred while migrating the database. Trying to ensure database is created...");
        try
        {
            // Fallback: try to ensure database is created
            context.Database.EnsureCreated();
            logger.LogWarning("Database ensured using EnsureCreated(). Migrations may not be applied.");
        }
        catch (Exception ex2)
        {
            logger.LogError(ex2, "Failed to create database. Application may not work correctly.");
        }
    }

    var hasMigrations = context.Database.GetMigrations().Any();
    if (!hasMigrations)
    {
        if (context.Database.EnsureCreated())
        {
            logger.LogInformation("Database schema created via EnsureCreated() because no migrations were found.");
        }
    }
    // Seed default admin user
    try
    {
        const string defaultAdminLogin = "admin";
        const string defaultAdminPassword = "administrator";

        if (!context.Users.Any(u => u.Login == defaultAdminLogin))
        {
            var now = DateTime.UtcNow;
            context.Users.Add(new User
            {
                Login = defaultAdminLogin,
                HashPassword = BCrypt.Net.BCrypt.HashPassword(defaultAdminPassword),
                CreatedAt = now,
                UpdatedAt = now
            });

            context.SaveChanges();
            logger.LogInformation("Default admin user created with login '{Login}'", defaultAdminLogin);
        }
        else
        {
            logger.LogInformation("Default admin user '{Login}' already exists", defaultAdminLogin);
        }
    }
    catch (Exception seedEx)
    {
        logger.LogError(seedEx, "An error occurred while ensuring default admin user exists");
    }

    try
    {
        var connection = context.Database.GetDbConnection();
        if (connection.State != ConnectionState.Open)
        {
            connection.Open();
        }

        using (var checkCommand = connection.CreateCommand())
        {
            checkCommand.CommandText = """
                SELECT
                    SUM(CASE WHEN table_name = 'tg_ids' AND column_name = 'chat_id' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN table_name = 'orders' THEN 1 ELSE 0 END)
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND (table_name = 'tg_ids' OR table_name = 'orders');
                """;

            using var reader = checkCommand.ExecuteReader();
            int chatIdExists = 0;
            int ordersExists = 0;
            if (reader.Read())
            {
                chatIdExists = reader.IsDBNull(0) ? 0 : reader.GetInt32(0);
                ordersExists = reader.IsDBNull(1) ? 0 : reader.GetInt32(1);
            }
            reader.Close();

            if (chatIdExists == 0)
            {
                using var alterCommand = connection.CreateCommand();
                alterCommand.CommandText = "ALTER TABLE tg_ids ADD COLUMN chat_id BIGINT NULL;";
                alterCommand.ExecuteNonQuery();
            }

            if (ordersExists == 0)
            {
                using var createOrders = connection.CreateCommand();
                createOrders.CommandText = """
                    CREATE TABLE orders (
                        id uuid PRIMARY KEY,
                        car_uuid varchar(64) NOT NULL,
                        client_telegram_id varchar(100),
                        tg_id_id uuid NULL,
                        created_at timestamp without time zone NOT NULL,
                        updated_at timestamp without time zone NOT NULL,
                        created_by varchar(255),
                        updated_by varchar(255),
                        CONSTRAINT fk_orders_tg_ids FOREIGN KEY (tg_id_id) REFERENCES tg_ids(id) ON DELETE SET NULL
                    );
                    """;
                createOrders.ExecuteNonQuery();
            }
        }

        using (var indexCommand = connection.CreateCommand())
        {
            indexCommand.CommandText = """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_tg_ids_chat_id
                ON tg_ids (chat_id)
                WHERE chat_id IS NOT NULL;
                """;
            indexCommand.ExecuteNonQuery();

            indexCommand.CommandText = """
                CREATE INDEX IF NOT EXISTS ix_orders_created_at ON orders (created_at DESC);
                """;
            indexCommand.ExecuteNonQuery();

            indexCommand.CommandText = """
                CREATE INDEX IF NOT EXISTS ix_orders_car_uuid ON orders (car_uuid);
                """;
            indexCommand.ExecuteNonQuery();
        }
    }
    catch (Exception columnEx)
    {
        logger.LogError(columnEx, "Failed to ensure chat_id column exists on table tg_ids");
    }

}

// Configure pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

// Health check endpoint
app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow }));

app.Run();







