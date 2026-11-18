import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';

@Injectable()
export class SkillsService {
  constructor(private readonly prisma: PrismaService) {}

  findMine(userId: string) {
    return this.prisma.skill.findMany({ where: { userId }, orderBy: { createdAt: 'asc' } });
  }

  /** Adds any of the given names the user doesn't already have. Existing ones are left alone. */
  async addMany(userId: string, names: string[]) {
    const unique = [...new Set(names.map((n) => n.trim()).filter(Boolean))];
    if (unique.length > 0) {
      await this.prisma.skill.createMany({
        data: unique.map((name) => ({ userId, name })),
        skipDuplicates: true,
      });
    }
    return this.findMine(userId);
  }

  async remove(userId: string, skillId: string) {
    await this.prisma.skill.deleteMany({ where: { id: skillId, userId } });
    return this.findMine(userId);
  }
}
