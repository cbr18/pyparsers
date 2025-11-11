using Microsoft.EntityFrameworkCore;
using Adminservice.Models;

namespace Adminservice.Data;

public class AdminDbContext : DbContext
{
    public AdminDbContext(DbContextOptions<AdminDbContext> options) : base(options)
    {
    }

    public DbSet<User> Users { get; set; }
    public DbSet<TgId> TgIds { get; set; }
    public DbSet<Order> Orders { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<User>(entity =>
        {
            entity.HasIndex(e => e.Login).IsUnique();
            entity.HasOne(e => e.TgId)
                  .WithMany(t => t.Users)
                  .HasForeignKey(e => e.TgIdId)
                  .OnDelete(DeleteBehavior.SetNull);
        });

        modelBuilder.Entity<TgId>(entity =>
        {
            entity.HasIndex(e => e.TelegramId).IsUnique();
            entity.HasIndex(e => e.ChatId).IsUnique().HasFilter("\"chat_id\" IS NOT NULL");
        });

        modelBuilder.Entity<Order>(entity =>
        {
            entity.HasIndex(e => e.CarUuid);
            entity.HasIndex(e => e.CreatedAt);
            entity.Property(e => e.ClientTelegramId)
                  .HasMaxLength(100);
        });

    }

    public override int SaveChanges()
    {
        UpdateTimestamps();
        return base.SaveChanges();
    }

    public override Task<int> SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        UpdateTimestamps();
        return base.SaveChangesAsync(cancellationToken);
    }

    private void UpdateTimestamps()
    {
        var entries = ChangeTracker.Entries<BaseRecord>();
        
        foreach (var entry in entries)
        {
            if (entry.State == EntityState.Added)
            {
                entry.Entity.CreatedAt = DateTime.UtcNow;
                entry.Entity.UpdatedAt = DateTime.UtcNow;
            }
            else if (entry.State == EntityState.Modified)
            {
                entry.Entity.UpdatedAt = DateTime.UtcNow;
            }
        }
    }
} 