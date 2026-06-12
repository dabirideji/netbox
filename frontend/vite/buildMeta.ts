import fs from 'node:fs';
import path from 'node:path';

interface FrontendAppConfig {
  openSource?: boolean;
}

export interface BuildMeta {
  version: string;
  openSource: boolean;
  appId: string;
  copyright: string;
  builderName: string;
  builderVersion: string;
  author: string;
}

function readYamlValue(source: string, key: string): string {
  const match = source.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
  return match?.[1]?.trim() ?? '';
}

export function readBuildMeta(projectRoot: string, appConfig: FrontendAppConfig = {}): BuildMeta {
  const electronPackagePath = path.resolve(projectRoot, 'electron', 'package.json');
  const builderConfigPath = path.resolve(projectRoot, 'electron', 'electron-builder.yml');

  const electronPackage = fs.existsSync(electronPackagePath)
    ? (JSON.parse(fs.readFileSync(electronPackagePath, 'utf-8')) as {
        version?: string;
        author?: string;
        devDependencies?: Record<string, string>;
      })
    : {};

  const builderConfig = fs.existsSync(builderConfigPath)
    ? fs.readFileSync(builderConfigPath, 'utf-8')
    : '';

  const builderVersion =
    electronPackage.devDependencies?.['electron-builder']?.replace(/^[\^~>=<]*/, '') ?? 'unknown';

  return {
    version: electronPackage.version ?? '0.0.0',
    openSource: Boolean(appConfig.openSource),
    appId: readYamlValue(builderConfig, 'appId') || 'com.netbox.monitor',
    copyright: readYamlValue(builderConfig, 'copyright'),
    builderName: 'electron-builder',
    builderVersion,
    author: electronPackage.author ?? 'Netbox',
  };
}
