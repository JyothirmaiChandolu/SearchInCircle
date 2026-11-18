import { Controller, Get, Req, UseGuards } from '@nestjs/common';
import type { Request } from 'express';
import { CognitoAuthGuard } from './cognito-auth.guard.js';

@Controller('auth')
export class AuthController {
  @Get('me')
  @UseGuards(CognitoAuthGuard)
  me(@Req() request: Request) {
    return { sub: request.user?.sub };
  }
}
