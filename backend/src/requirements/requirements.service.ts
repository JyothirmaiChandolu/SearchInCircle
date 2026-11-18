import { ForbiddenException, Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import type { CreateRequirementDto, UpdateRequirementDto } from './dto/requirement.dto.js';

@Injectable()
export class RequirementsService {
  constructor(private readonly prisma: PrismaService) {}

  findMine(publisherId: string) {
    return this.prisma.requirement.findMany({ where: { publisherId }, orderBy: { createdAt: 'desc' } });
  }

  create(publisherId: string, dto: CreateRequirementDto) {
    return this.prisma.requirement.create({
      data: { publisherId, ...dto, visibleSubscriberIds: [] },
    });
  }

  async update(userId: string, requirementId: string, dto: UpdateRequirementDto) {
    await this.assertOwnership(userId, requirementId);
    return this.prisma.requirement.update({ where: { id: requirementId }, data: dto });
  }

  async remove(userId: string, requirementId: string) {
    await this.assertOwnership(userId, requirementId);
    await this.prisma.requirement.delete({ where: { id: requirementId } });
  }

  private async assertOwnership(userId: string, requirementId: string) {
    const requirement = await this.prisma.requirement.findUnique({
      where: { id: requirementId },
      select: { publisherId: true },
    });
    if (!requirement) throw new NotFoundException('Requirement not found');
    if (requirement.publisherId !== userId) {
      throw new ForbiddenException('Only the requirement’s creator can change it');
    }
  }
}
