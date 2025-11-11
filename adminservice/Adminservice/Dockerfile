FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy csproj and restore dependencies
COPY ["Adminservice.csproj", "./"]
RUN dotnet restore "Adminservice.csproj"

# Copy everything else and build
COPY . .
RUN dotnet build "Adminservice.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "Adminservice.csproj" -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

# Install wget for healthcheck
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

EXPOSE 8080

COPY --from=publish /app/publish .

ENTRYPOINT ["dotnet", "Adminservice.dll"] 