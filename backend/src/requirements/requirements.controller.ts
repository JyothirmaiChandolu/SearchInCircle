import { BadRequestException, Body, Controller, Delete, Get, Param, Patch, Post, Req, UseGuards } from '@nestjs/common';
import type { Request } from 'express';
import { CognitoAuthGuard } from '../auth/cognito-auth.guard.js';
import { createRequirementSchema, updateRequirementSchema } from './dto/requirement.dto.js';
import { RequirementsService } from './requirements.service.js';

@Controller('requirements')
@UseGuards(CognitoAuthGuard)
export class RequirementsController {
  constructor(private readonly requirementsService: RequirementsService) {}

  @Get('mine')
  mine(@Req() request: Request) {
    return this.requirementsService.findMine(request.user!.sub);
  }

  @Post()
  async create(@Req() request: Request, @Body() body: unknown) {
    const result = createRequirementSchema.safeParse(body);
    if (!result.success) {
      throw new BadRequestException(result.error.issues.map((i) => i.message).join(', '));
    }
    return this.requirementsService.create(request.user!.sub, result.data);
  }

  @Patch(':id')
  async update(@Req() request: Request, @Param('id') id: string, @Body() body: unknown) {
    const result = updateRequirementSchema.safeParse(body);
    if (!result.success) {
      throw new BadRequestException(result.error.issues.map((i) => i.message).join(', '));
    }
    return this.requirementsService.update(request.user!.sub, id, result.data);
  }

  @Delete(':id')
  async remove(@Req() request: Request, @Param('id') id: string) {
    await this.requirementsService.remove(request.user!.sub, id);
    return { success: true };
  }
}
