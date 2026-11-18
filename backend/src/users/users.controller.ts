import { BadRequestException, Body, Controller, Get, NotFoundException, Post, Req, UseGuards } from '@nestjs/common';
import type { Request } from 'express';
import { CognitoAuthGuard } from '../auth/cognito-auth.guard.js';
import { createUserSchema } from './dto/create-user.dto.js';
import { UsersService } from './users.service.js';

@Controller('users')
@UseGuards(CognitoAuthGuard)
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get('me')
  async me(@Req() request: Request) {
    const user = await this.usersService.findByCognitoSub(request.user!.sub);
    if (!user) {
      throw new NotFoundException('Onboarding not completed yet');
    }
    return user;
  }

  @Post()
  async create(@Req() request: Request, @Body() body: unknown) {
    const result = createUserSchema.safeParse(body);
    if (!result.success) {
      throw new BadRequestException(result.error.issues.map((i) => i.message).join(', '));
    }
    return this.usersService.create(request.user!.sub, result.data);
  }
}
