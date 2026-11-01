SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.IndicatorRuleVersion', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.IndicatorRuleVersion (
        version_id int IDENTITY(1,1) NOT NULL PRIMARY KEY,
        cancer_group_key nvarchar(50) NOT NULL,
        version_name nvarchar(100) NOT NULL,
        rules_json nvarchar(max) NOT NULL,
        created_by nvarchar(100) NOT NULL,
        created_at datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_IndicatorRuleVersion_Name UNIQUE (cancer_group_key, version_name),
        CONSTRAINT CK_IndicatorRuleVersion_Json CHECK (ISJSON(rules_json) = 1)
    );

    -- Preserve IDs of previously created oral-cancer versions and their links.
    IF OBJECT_ID(N'dbo.OralIndicatorRuleVersion', N'U') IS NOT NULL
    BEGIN
        EXEC sys.sp_executesql N'
            SET IDENTITY_INSERT dbo.IndicatorRuleVersion ON;
            INSERT INTO dbo.IndicatorRuleVersion
                (version_id, cancer_group_key, version_name, rules_json, created_by, created_at)
            SELECT version_id, N''Oral_Cavity'', version_name, rules_json, created_by, created_at
            FROM dbo.OralIndicatorRuleVersion;
            SET IDENTITY_INSERT dbo.IndicatorRuleVersion OFF;';
    END
END

COMMIT TRANSACTION;
