SET NOCOUNT ON;

IF COL_LENGTH(N'dbo.Indicator_definition_metadata', N'target_value') IS NULL
BEGIN
    ALTER TABLE dbo.Indicator_definition_metadata
    ADD target_value decimal(5, 2) NULL;
END;

IF COL_LENGTH(N'dbo.Indicator_definition_metadata', N'target_operator') IS NULL
BEGIN
    ALTER TABLE dbo.Indicator_definition_metadata
    ADD target_operator nvarchar(2) NULL;
END;

