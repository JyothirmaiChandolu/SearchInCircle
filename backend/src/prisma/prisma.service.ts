import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaPg } from '@prisma/adapter-pg';
import { PrismaClient } from '../generated/prisma/client.js';

const RDS_CA_BUNDLE_PATH = join(import.meta.dirname, '../../certs/rds-global-bundle.pem');

@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit, OnModuleDestroy {
  constructor(configService: ConfigService) {
    const connectionString = configService.getOrThrow<string>('DATABASE_URL');
    const requiresSsl = /[?&]sslmode=require\b/.test(connectionString);
    const strippedConnectionString = connectionString.replace(/[?&]sslmode=require\b/, '');

    super({
      adapter: new PrismaPg({
        connectionString: strippedConnectionString,
        ...(requiresSsl && {
          ssl: { ca: readFileSync(RDS_CA_BUNDLE_PATH, 'utf8'), rejectUnauthorized: true },
        }),
      }),
    });
  }

  async onModuleInit() {
    await this.$connect();
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }
}
