import { BadRequestException, Body, Controller, Delete, Get, Param, Patch, Post, Req, UseGuards } from '@nestjs/common';
import type { Request } from 'express';
import { CognitoAuthGuard } from '../auth/cognito-auth.guard.js';
import { createTagSchema, updateTagSchema } from './dto/create-tag.dto.js';
import { lookupPersonSchema } from './dto/lookup-person.dto.js';
import { TagsService } from './tags.service.js';

@Controller()
@UseGuards(CognitoAuthGuard)
export class TagsController {
  constructor(private readonly tagsService: TagsService) {}

  @Post('tagged-people/lookup')
  async lookup(@Body() body: unknown) {
    const result = lookupPersonSchema.safeParse(body);
    if (!result.success) {
      throw new BadRequestException(result.error.issues.map((i) => i.message).join(', '));
    }
    return this.tagsService.lookupPerson(result.data);
  }

  @Get('tags/mine')
  mine(@Req() request: Request) {
    return this.tagsService.findMine(request.user!.sub);
  }

  @Post('tags')
  async create(@Req() request: Request, @Body() body: unknown) {
    const result = createTagSchema.safeParse(body);
    if (!result.success) {
      throw new BadRequestException(result.error.issues.map((i) => i.message).join(', '));
    }
    return this.tagsService.create(request.user!.sub, result.data);
  }

  @Patch('tags/:id')
  async update(@Req() request: Request, @Param('id') id: string, @Body() body: unknown) {
    const result = updateTagSchema.safeParse(body);
    if (!result.success) {
      throw new BadRequestException(result.error.issues.map((i) => i.message).join(', '));
    }
    return this.tagsService.update(request.user!.sub, id, result.data);
  }

  @Delete('tags/:id')
  async remove(@Req() request: Request, @Param('id') id: string) {
    await this.tagsService.remove(request.user!.sub, id);
    return { success: true };
  }
}
