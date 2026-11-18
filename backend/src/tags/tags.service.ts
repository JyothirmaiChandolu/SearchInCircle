import { ForbiddenException, Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import type { CreateTagDto, UpdateTagDto } from './dto/create-tag.dto.js';
import type { LookupPersonDto } from './dto/lookup-person.dto.js';

@Injectable()
export class TagsService {
  constructor(private readonly prisma: PrismaService) {}

  /** Preview-only lookup used before creating a tag — confirms whether this person is
   * already known without exposing who tagged them or what any tag says about them. */
  async lookupPerson(dto: LookupPersonDto) {
    const person = await this.prisma.taggedPerson.findFirst({
      where: {
        OR: [dto.phone ? { phone: dto.phone } : undefined, dto.email ? { email: dto.email } : undefined].filter(
          (c): c is NonNullable<typeof c> => c !== undefined,
        ),
      },
      select: { id: true, name: true, country: true },
    });
    return person;
  }

  findMine(userId: string) {
    return this.prisma.tag.findMany({
      where: { creatorId: userId },
      include: { person: { select: { id: true, name: true, phone: true, email: true, country: true } } },
      orderBy: { createdAt: 'desc' },
    });
  }

  async create(creatorId: string, dto: CreateTagDto) {
    const person = dto.personId
      ? await this.prisma.taggedPerson.findUniqueOrThrow({ where: { id: dto.personId } })
      : await this.resolvePerson(dto);

    return this.prisma.tag.create({
      data: {
        creatorId,
        personId: person.id,
        nickname: dto.nickname,
        description: dto.description,
        skills: dto.skills,
        tools: dto.tools,
        yearsExperience: dto.yearsExperience,
        certifications: dto.certifications,
        isOpen: dto.isOpen,
      },
      include: { person: { select: { id: true, name: true, phone: true, email: true, country: true } } },
    });
  }

  private async resolvePerson(dto: CreateTagDto) {
    const existing = dto.phone || dto.email ? await this.lookupPerson({ phone: dto.phone, email: dto.email }) : null;
    if (existing) {
      return this.prisma.taggedPerson.findUniqueOrThrow({ where: { id: existing.id } });
    }
    return this.prisma.taggedPerson.create({
      data: { name: dto.name, phone: dto.phone, email: dto.email, country: dto.country },
    });
  }

  async update(userId: string, tagId: string, dto: UpdateTagDto) {
    await this.assertOwnership(userId, tagId);
    return this.prisma.tag.update({
      where: { id: tagId },
      data: dto,
      include: { person: { select: { id: true, name: true, phone: true, email: true, country: true } } },
    });
  }

  async remove(userId: string, tagId: string) {
    await this.assertOwnership(userId, tagId);
    await this.prisma.tag.delete({ where: { id: tagId } });
  }

  private async assertOwnership(userId: string, tagId: string) {
    const tag = await this.prisma.tag.findUnique({ where: { id: tagId }, select: { creatorId: true } });
    if (!tag) throw new NotFoundException('Tag not found');
    if (tag.creatorId !== userId) throw new ForbiddenException('Only the tag’s creator can edit or remove it');
  }
}
