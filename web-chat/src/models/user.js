export default class User {
  constructor(name, password) {
    this.name = name;
    this.password = password;
    this.auth = null;
  }
}
